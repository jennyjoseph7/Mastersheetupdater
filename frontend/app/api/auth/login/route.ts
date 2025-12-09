import { NextResponse } from "next/server"

export async function POST(request: Request) {
  try {
    const { email, password } = await request.json()

    console.log("[v0] Login attempt:", { email })

    if (email === "user@iamdave.ai" && password === "12345678") {
      const user = {
        id: "dealer_001",
        email: "user@iamdave.ai",
        name: "Dave AI Dealer",
        credits: 5000,
      }

      const token = `token_${Date.now()}_${Math.random().toString(36).substring(7)}`

      console.log("[v0] Login successful for:", email)

      return NextResponse.json(
        {
          success: true,
          token,
          user,
        },
        { status: 200 },
      )
    }

    console.log("[v0] Login failed - invalid credentials")
    return NextResponse.json(
      {
        success: false,
        message: "Invalid email or password",
      },
      { status: 401 },
    )
  } catch (error) {
    console.error("[v0] Login error:", error)
    return NextResponse.json(
      {
        success: false,
        message: "An error occurred during login",
      },
      { status: 500 },
    )
  }
}
