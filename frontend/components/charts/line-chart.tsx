"use client"

import { useEffect, useRef, useState } from "react"
import * as d3 from "d3"

interface LineChartProps {
  data: Array<{
    name: string
    value: number
  }>
  width?: number
  height?: number
  xAxisLabel?: string
  yAxisLabel?: string
}

export function LineChart({ data, width = 500, height = 300, xAxisLabel, yAxisLabel }: LineChartProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [hoveredPoint, setHoveredPoint] = useState<number | null>(null)

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
      .scalePoint()
      .domain(data.map((d) => d.name))
      .range([0, innerWidth])
      .padding(0.5)

    const maxValue = d3.max(data, (d) => d.value) || 0
    const yMax = Math.ceil(maxValue * 1.1) // Add 10% padding to the top

    const y = d3.scaleLinear().domain([0, yMax]).nice().range([innerHeight, 0])

    // Create chart group
    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`)

    // Add gradient definitions
    const defs = svg.append("defs")

    // Create gradient for area
    const areaGradient = defs
      .append("linearGradient")
      .attr("id", "area-gradient")
      .attr("x1", "0%")
      .attr("y1", "0%")
      .attr("x2", "0%")
      .attr("y2", "100%")

    areaGradient.append("stop").attr("offset", "0%").attr("stop-color", "hsl(260, 98%, 31%)").attr("stop-opacity", 0.3)

    areaGradient
      .append("stop")
      .attr("offset", "100%")
      .attr("stop-color", "hsl(260, 98%, 31%)")
      .attr("stop-opacity", 0.1)

    // Add drop shadow filter
    const filter = defs.append("filter").attr("id", "point-shadow").attr("height", "130%")
    filter.append("feGaussianBlur").attr("in", "SourceAlpha").attr("stdDeviation", 2).attr("result", "blur")
    filter.append("feOffset").attr("in", "blur").attr("dx", 0).attr("dy", 1).attr("result", "offsetBlur")

    const feComponentTransfer = filter
      .append("feComponentTransfer")
      .attr("in", "offsetBlur")
      .attr("result", "offsetBlur")
    feComponentTransfer.append("feFuncA").attr("type", "linear").attr("slope", 0.5)

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
      .call((g) => g.selectAll("text").attr("class", "text-xs").attr("dy", "0.7em"))
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

    // Define line generator
    const line = d3
      .line<(typeof data)[0]>()
      .x((d) => x(d.name) || 0)
      .y((d) => y(d.value))
      .curve(d3.curveCardinal.tension(0.5)) // Use cardinal curve for smoother lines

    // Define area generator
    const area = d3
      .area<(typeof data)[0]>()
      .x((d) => x(d.name) || 0)
      .y0(innerHeight)
      .y1((d) => y(d.value))
      .curve(d3.curveCardinal.tension(0.5)) // Match the line curve

    // Add area with animation
    g.append("path")
      .datum(data)
      .attr("fill", "url(#area-gradient)")
      .attr("d", area)
      .attr("opacity", 0)
      .transition()
      .duration(1000)
      .attr("opacity", 0.8)

    // Add line with animation
    const linePath = g
      .append("path")
      .datum(data)
      .attr("fill", "none")
      .attr("stroke", "hsl(260, 98%, 31%)")
      .attr("stroke-width", 3)
      .attr("stroke-linejoin", "round")
      .attr("stroke-linecap", "round")
      .attr("d", line)
      .attr("stroke-dasharray", function () {
        const pathLength = (this as SVGPathElement).getTotalLength()
        return `${pathLength} ${pathLength}`
      })
      .attr("stroke-dashoffset", function () {
        return (this as SVGPathElement).getTotalLength()
      })
      .transition()
      .duration(1500)
      .ease(d3.easePolyOut)
      .attr("stroke-dashoffset", 0)

    // Add dots with animation
    data.forEach((d, i) => {
      // Create a group for each dot and its effects
      const dotGroup = g
        .append("g")
        .attr("class", `dot-group dot-group-${i}`)
        .attr("transform", `translate(${x(d.name) || 0}, ${y(d.value)})`)

      // Add a larger invisible circle for better hover detection
      dotGroup
        .append("circle")
        .attr("class", "hover-area")
        .attr("r", 15)
        .attr("fill", "transparent")
        .style("cursor", "pointer")
        .on("mouseenter", () => {
          setHoveredPoint(i)
          dotGroup.select(".dot").attr("r", 7).attr("filter", "url(#point-shadow)")

          // Show tooltip
          const tooltip = g
            .append("g")
            .attr("class", "tooltip")
            .attr("transform", `translate(${x(d.name) || 0}, ${y(d.value) - 20})`)

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
        .on("mouseleave", () => {
          setHoveredPoint(null)
          dotGroup.select(".dot").attr("r", 5).attr("filter", null)
          g.select(".tooltip").remove()
        })

      // Add the visible dot
      dotGroup
        .append("circle")
        .attr("class", "dot")
        .attr("r", 0)
        .attr("fill", "white")
        .attr("stroke", "hsl(260, 98%, 31%)")
        .attr("stroke-width", 2)
        .transition()
        .delay(1500 + i * 100)
        .duration(300)
        .attr("r", 5)
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
  }, [data, width, height, xAxisLabel, yAxisLabel, hoveredPoint])

  return (
    <div className="flex justify-center w-full">
      <svg ref={svgRef} width="100%" height={height} style={{ maxWidth: width }} className="mx-auto overflow-visible" />
    </div>
  )
}
