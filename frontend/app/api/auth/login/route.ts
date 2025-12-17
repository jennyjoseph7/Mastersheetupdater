import { NextResponse } from "next/server";
import axios from "axios";

export async function POST(request: Request) {
  try {
    const { email, password } = await request.json();

    console.log("[v0] Login attempt:", { email });

    if (email === "user@iamdave.ai" && password === "12345678") {
      const user = {
        id: "dealer_001",
        email: "user@iamdave.ai",
        name: "Dave AI Dealer",
        credits: 5000,
      };

      const token = `token_${Date.now()}_${Math.random().toString(36).substring(7)}`;

      console.log("[v0] Login successful for:", email);

      return NextResponse.json(
        {
          success: true,
          token,
          user,
        },
        { status: 200 },
      );
    }

    console.log("[v0] Login failed - invalid credentials");
    return NextResponse.json(
      {
        success: false,
        message: "Invalid email or password",
      },
      { status: 401 },
    );
  } catch (error) {
    console.error("[v0] Login error:", error);
    return NextResponse.json(
      {
        success: false,
        message: "An error occurred during login",
      },
      { status: 500 },
    );
  }
}

export async function POST(req: Request) {
  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ message: "Only POST requests allowed" }),
      { status: 405 },
    );
  }
  const data =  await req.json();
  const { token } =data;
  const secretKey = process.env.RECAPTCHA_SECRET_KEY;
  if (!token){
    return new Response(JSON.stringify({ message: "No token provided" }), {status: 405});
  }
  try{
    const response = await axios.post(`https://www.google.com/recaptcha/api/siteverify?secret=${secretKey}&response=${token}`);
    if (response.data.success){
      return new Response(JSON.stringify({ message: "Captcha verified" }), {status: 200});
    }else{
      return new Response(JSON.stringify({ message: "Captcha verification failed" }), {status: 401});
    }
  }catch(error){
    return new Response(JSON.stringify({ message: "Error verifying captcha" }), {status: 500});


}
