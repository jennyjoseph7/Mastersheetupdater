"use client"

import { useEffect, useRef, useState } from "react"
import * as d3 from "d3"

interface DonutChartProps {
  data: Array<{
    name: string
    value: number
    color: string
  }>
  width?: number
  height?: number
  innerRadius?: number
  outerRadius?: number
  title?: string
  description?: string
}

export function DonutChart({
  data,
  width = 300,
  height = 300,
  innerRadius = 60,
  outerRadius = 110,
  title,
  description,
}: DonutChartProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [hoveredSegment, setHoveredSegment] = useState<string | null>(null)

  useEffect(() => {
    if (!svgRef.current || !data.length) return

    const svg = d3.select(svgRef.current)
    svg.selectAll("*").remove()

    const pie = d3
      .pie<(typeof data)[0]>()
      .value((d) => d.value)
      .sort(null) // Prevent automatic sorting

    const arcs = pie(data)

    const arc = d3
      .arc<d3.PieArcDatum<(typeof data)[0]>>()
      .innerRadius(innerRadius)
      .outerRadius(outerRadius)
      .cornerRadius(3) // Slightly rounded corners

    const g = svg.append("g").attr("transform", `translate(${width / 2}, ${height / 2})`)

    // Add drop shadow filter
    const defs = svg.append("defs")
    const filter = defs.append("filter").attr("id", "drop-shadow").attr("height", "130%")

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

    // Draw segments with animation
    g.selectAll("path")
      .data(arcs)
      .enter()
      .append("path")
      .attr("d", arc)
      .attr("fill", (d) => d.data.color)
      .attr("stroke", "white")
      .attr("stroke-width", 2)
      .style("opacity", (d) => (hoveredSegment === d.data.name ? 1 : 0.9))
      .on("mouseenter", (event, d) => {
        setHoveredSegment(d.data.name)
        d3.select(event.currentTarget)
          .transition()
          .duration(200)
          .attr("filter", "url(#drop-shadow)")
          .attr("transform", `scale(1.03)`)

        // Add tooltip with value
        const tooltip = g.append("g").attr("class", "tooltip").attr("text-anchor", "middle")

        tooltip.append("text").attr("class", "text-lg font-bold").text(`${d.data.value}%`).attr("dy", "0em")

        tooltip.append("text").attr("class", "text-sm text-muted-foreground").text(d.data.name).attr("dy", "1.5em")
      })
      .on("mouseleave", (event) => {
        setHoveredSegment(null)
        d3.select(event.currentTarget).transition().duration(200).attr("filter", null).attr("transform", `scale(1)`)

        // Remove tooltip
        g.select(".tooltip").remove()
      })

    // We're removing the central title and description as requested
  }, [data, width, height, innerRadius, outerRadius, title, description, hoveredSegment])

  return (
    <div className="flex flex-col items-center w-full">
      <svg ref={svgRef} width="100%" height={height} style={{ maxWidth: width }} className="mx-auto" />
      <div className="flex flex-wrap justify-center gap-3 mt-3 px-2 w-full">
        {data.map((item) => (
          <div
            key={item.name}
            className={`flex items-center gap-1.5 px-2 py-1 rounded-full transition-colors ${
              hoveredSegment === item.name ? "bg-muted" : ""
            }`}
            onMouseEnter={() => setHoveredSegment(item.name)}
            onMouseLeave={() => setHoveredSegment(null)}
          >
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
            <span className="text-xs font-medium">
              {item.name}: {item.value}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
