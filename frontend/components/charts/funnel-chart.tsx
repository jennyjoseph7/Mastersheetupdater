"use client"

import { useEffect, useRef } from "react"
import * as d3 from "d3"

interface FunnelChartProps {
  data: Array<{
    name: string
    value: number
  }>
  width?: number
  height?: number
}

export function FunnelChart({ data, width = 500, height = 300 }: FunnelChartProps) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current || !data.length) return

    const svg = d3.select(svgRef.current)
    svg.selectAll("*").remove()

    const margin = { top: 20, right: 30, bottom: 20, left: 30 }
    const innerWidth = width - margin.left - margin.right
    const innerHeight = height - margin.top - margin.bottom

    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`)

    // Add drop shadow filter
    const defs = svg.append("defs")
    const filter = defs.append("filter").attr("id", "funnel-shadow").attr("height", "130%")

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

    // Calculate the maximum value for scaling
    const maxValue = d3.max(data, (d) => d.value) || 100

    // Create color scale for gradient effect using #39019a color scheme
    const colorScale = d3
      .scaleLinear<string>()
      .domain([0, data.length - 1])
      .range(["hsl(260, 98%, 31%)", "hsl(260, 70%, 50%)"])
      .interpolate(d3.interpolateHcl)

    // Calculate the height of each segment
    const segmentHeight = innerHeight / data.length

    // Draw the funnel segments with animation
    data.forEach((d, i) => {
      // Calculate widths for top and bottom of trapezoid
      const topWidth = ((i === 0 ? d.value : data[i - 1].value) / maxValue) * innerWidth
      const bottomWidth = (d.value / maxValue) * innerWidth

      // Calculate x positions
      const topLeftX = (innerWidth - topWidth) / 2
      const topRightX = topLeftX + topWidth
      const bottomLeftX = (innerWidth - bottomWidth) / 2
      const bottomRightX = bottomLeftX + bottomWidth

      // Calculate y positions
      const topY = i * segmentHeight
      const bottomY = (i + 1) * segmentHeight

      // Create points for the trapezoid
      const points = [
        [topLeftX, topY],
        [topRightX, topY],
        [bottomRightX, bottomY],
        [bottomLeftX, bottomY],
      ]
        .map((p) => p.join(","))
        .join(" ")

      // Create gradient for each segment
      const gradientId = `funnel-gradient-${i}`
      const gradient = defs
        .append("linearGradient")
        .attr("id", gradientId)
        .attr("x1", "0%")
        .attr("y1", "0%")
        .attr("x2", "100%")
        .attr("y2", "0%")

      gradient
        .append("stop")
        .attr("offset", "0%")
        .attr("stop-color", d3.color(colorScale(i))?.darker(0.3) as string)

      gradient.append("stop").attr("offset", "100%").attr("stop-color", colorScale(i))

      // Draw the trapezoid with animation
      const segment = g
        .append("polygon")
        .attr("points", points)
        .attr("fill", `url(#${gradientId})`)
        .attr("stroke", "white")
        .attr("stroke-width", 1.5)
        .attr("class", `segment-${i}`)
        .attr("opacity", 0)

      segment
        .transition()
        .duration(200)
        .delay(i * 100)
        .attr("opacity", 0.9)

      segment
        .on("mouseenter", function () {
          d3.select(this)
            .attr("filter", "url(#funnel-shadow)")
            .attr("opacity", 1)
            .attr("transform", `translate(0, -2)`)
        })
        .on("mouseleave", function () {
          d3.select(this).attr("filter", null).attr("opacity", 0.9).attr("transform", `translate(0, 0)`)
        })

      // Add the label inside the trapezoid
      g.append("text")
        .attr("x", innerWidth / 2)
        .attr("y", topY + (bottomY - topY) / 2)
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "middle")
        .attr("fill", "white")
        .attr("class", "text-xs font-medium")
        .attr("opacity", 0)
        .text(d.name)
        .transition()
        .duration(200)
        .delay(i * 100 + 100)
        .attr("opacity", 1)

      // Add the percentage on the right side
      g.append("text")
        .attr("x", innerWidth + 10)
        .attr("y", topY + (bottomY - topY) / 2)
        .attr("text-anchor", "start")
        .attr("dominant-baseline", "middle")
        .attr("class", "text-xs font-medium")
        .attr("opacity", 0)
        .text(`${d.value}%`)
        .transition()
        .duration(200)
        .delay(i * 100 + 100)
        .attr("opacity", 1)
    })
  }, [data, width, height])

  return (
    <div className="flex flex-col items-center w-full">
      <svg ref={svgRef} width="100%" height={height} style={{ maxWidth: width }} className="mx-auto" />
    </div>
  )
}
