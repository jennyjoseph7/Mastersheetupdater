"use client"

import { useEffect, useRef, useState } from "react"
import * as d3 from "d3"

interface BarChartProps {
  data: Array<{
    name: string
    value: number
  }>
  width?: number
  height?: number
  xAxisLabel?: string
  yAxisLabel?: string
}

export function BarChart({ data, width = 500, height = 300, xAxisLabel, yAxisLabel }: BarChartProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [hoveredBar, setHoveredBar] = useState<string | null>(null)

  useEffect(() => {
    if (!svgRef.current || !data.length) return

    // Clear previous chart
    const svg = d3.select(svgRef.current)
    svg.selectAll("*").remove()

    // Set margins and dimensions
    const margin = { top: 20, right: 30, bottom: 50, left: 60 }
    const innerWidth = width - margin.left - margin.right
    const innerHeight = height - margin.top - margin.bottom

    // Create scales
    const x = d3
      .scaleBand()
      .domain(data.map((d) => d.name))
      .range([0, innerWidth])
      .padding(0.3)

    const maxValue = d3.max(data, (d) => d.value) || 0
    const yMax = Math.ceil(maxValue * 1.1) // Add 10% padding to the top

    const y = d3.scaleLinear().domain([0, yMax]).nice().range([innerHeight, 0])

    // Create chart group
    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`)

    // Add gradient definitions
    const defs = svg.append("defs")

    // Create gradient for bars using #39019a color scheme
    const gradient = defs
      .append("linearGradient")
      .attr("id", "bar-gradient")
      .attr("x1", "0%")
      .attr("y1", "0%")
      .attr("x2", "0%")
      .attr("y2", "100%")

    gradient.append("stop").attr("offset", "0%").attr("stop-color", "hsl(260, 98%, 31%)")
    gradient.append("stop").attr("offset", "100%").attr("stop-color", "hsl(260, 70%, 50%)")

    // Add drop shadow filter
    const filter = defs.append("filter").attr("id", "bar-shadow").attr("height", "130%")
    filter.append("feGaussianBlur").attr("in", "SourceAlpha").attr("stdDeviation", 3).attr("result", "blur")
    filter.append("feOffset").attr("in", "blur").attr("dx", 1).attr("dy", 1).attr("result", "offsetBlur")

    const feComponentTransfer = filter
      .append("feComponentTransfer")
      .attr("in", "offsetBlur")
      .attr("result", "offsetBlur")
    feComponentTransfer.append("feFuncA").attr("type", "linear").attr("slope", 0.3)

    const feMerge = filter.append("feMerge")
    feMerge.append("feMergeNode").attr("in", "offsetBlur")
    feMerge.append("feMergeNode").attr("in", "SourceGraphic")

    // Add grid lines
    g.append("g")
      .attr("class", "grid")
      .call(
        d3
          .axisLeft(y)
          .ticks(5)
          .tickSize(-innerWidth)
          .tickFormat(() => ""),
      )
      .call((g) => g.select(".domain").remove())
      .call((g) => g.selectAll(".tick line").attr("stroke", "rgba(0, 0, 0, 0.1)").attr("stroke-dasharray", "2,2"))

    // Add x-axis
    g.append("g")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(d3.axisBottom(x))
      .call((g) =>
        g
          .selectAll("text")
          .attr("class", "text-xs")
          .attr("dy", "0.7em")
          .attr("transform", "rotate(0)")
          .style("text-anchor", "middle"),
      )
      .call((g) => g.select(".domain").attr("stroke", "rgba(0, 0, 0, 0.2)"))
      .call((g) => g.selectAll(".tick line").attr("stroke", "rgba(0, 0, 0, 0.2)"))

    // Add y-axis
    g.append("g")
      .call(
        d3
          .axisLeft(y)
          .ticks(5)
          .tickFormat((d) => `${d}`),
      )
      .call((g) => g.selectAll("text").attr("class", "text-xs"))
      .call((g) => g.select(".domain").attr("stroke", "rgba(0, 0, 0, 0.2)"))
      .call((g) => g.selectAll(".tick line").attr("stroke", "rgba(0, 0, 0, 0.2)"))

    // Add bars with animation
    g.selectAll(".bar")
      .data(data)
      .enter()
      .append("rect")
      .attr("class", (d) => `bar bar-${d.name.replace(/\s+/g, "-").toLowerCase()}`)
      .attr("x", (d) => x(d.name) || 0)
      .attr("width", x.bandwidth())
      .attr("y", innerHeight)
      .attr("height", 0)
      .attr("rx", 4) // Rounded corners
      .attr("fill", "url(#bar-gradient)")
      .attr("opacity", (d) => (hoveredBar === d.name ? 1 : 0.9))
      .transition()
      .duration(800)
      .delay((_, i) => i * 100)
      .attr("y", (d) => y(d.value))
      .attr("height", (d) => innerHeight - y(d.value))

    // Add interaction after transition
    g.selectAll(".bar")
      .on("mouseenter", function (event, d) {
        setHoveredBar(d.name)
        d3.select(this).attr("filter", "url(#bar-shadow)").attr("opacity", 1)

        // Show tooltip
        const tooltip = g
          .append("g")
          .attr("class", "tooltip")
          .attr("transform", `translate(${(x(d.name) || 0) + x.bandwidth() / 2}, ${y(d.value) - 15})`)

        tooltip
          .append("rect")
          .attr("x", -25)
          .attr("y", -25)
          .attr("width", 50)
          .attr("height", 25)
          .attr("rx", 4)
          .attr("fill", "rgba(0, 0, 0, 0.8)")

        tooltip
          .append("text")
          .attr("x", 0)
          .attr("y", -10)
          .attr("text-anchor", "middle")
          .attr("fill", "white")
          .attr("class", "text-xs font-medium")
          .text(d.value)
      })
      .on("mouseleave", function () {
        setHoveredBar(null)
        d3.select(this).attr("filter", null).attr("opacity", 0.9)

        // Remove tooltip
        g.select(".tooltip").remove()
      })

    // Add x-axis label if provided
    if (xAxisLabel) {
      g.append("text")
        .attr("class", "text-xs text-muted-foreground")
        .attr("text-anchor", "middle")
        .attr("x", innerWidth / 2)
        .attr("y", innerHeight + margin.bottom - 10)
        .text(xAxisLabel)
    }

    // Add y-axis label if provided
    if (yAxisLabel) {
      g.append("text")
        .attr("class", "text-xs text-muted-foreground")
        .attr("text-anchor", "middle")
        .attr("transform", "rotate(-90)")
        .attr("x", -innerHeight / 2)
        .attr("y", -margin.left + 15)
        .text(yAxisLabel)
    }

    // Add value labels on top of bars
    g.selectAll(".bar-value")
      .data(data)
      .enter()
      .append("text")
      .attr("class", "bar-value text-xs font-medium")
      .attr("text-anchor", "middle")
      .attr("x", (d) => (x(d.name) || 0) + x.bandwidth() / 2)
      .attr("y", (d) => y(d.value) - 5)
      .attr("opacity", 0)
      .text((d) => d.value)
      .transition()
      .duration(800)
      .delay((_, i) => i * 100 + 300)
      .attr("opacity", 1)
  }, [data, width, height, xAxisLabel, yAxisLabel, hoveredBar])

  return (
    <div className="flex justify-center w-full">
      <svg ref={svgRef} width="100%" height={height} style={{ maxWidth: width }} className="mx-auto overflow-visible" />
    </div>
  )
}
