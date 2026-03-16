import { NextResponse } from "next/server";
import axios from "axios";

export async function POST(request: Request) {
  try {
    const { email, password, captchaToken } = await request.json();

    console.log("[autoNgage] Login attempt:", { email });

    if (!captchaToken) {
      return NextResponse.json(
        { success: false, message: "Captcha token missing" },
        { status: 400 }
      );
    }

    const secretKey = process.env.RECAPTCHA_SECRET_KEY;
    console.log("[autoNgage] reCAPTCHA secret key status:", secretKey ? "Loaded" : "Not found", secretKey);
    const captchaResponse = await axios.post(
      `https://www.google.com/recaptcha/api/siteverify`,
      null,
      {
        params: {
          secret: secretKey,
          response: captchaToken,
        },
      }
    );

    if (!captchaResponse.data.success) {
      return NextResponse.json(
        { success: false, message: "Captcha verification failed" },
        { status: 401 }
      );
    }

    if (email === "user@iamdave.ai" && password === "12345678") {
      const user = {
        id: "dealer_001",
        email: "user@iamdave.ai",
        name: "Dave AI Dealer",
        credits: 5000,
      };

      const token = `token_${Date.now()}_${Math.random()
        .toString(36)
        .substring(7)}`;

      console.log("[autoNgage] Login successful for:", email);

      return NextResponse.json(
        {
          success: true,
          token,
          user,
        },
        { status: 200 }
      );
    }

    return NextResponse.json(
      {
        success: false,
        message: "Invalid email or password",
      },
      { status: 401 }
    );
  } catch (error) {
    console.error("[autoNgage] Login error:", error);
    return NextResponse.json(
      {
        success: false,
        message: "An error occurred during login",
      },
      { status: 500 }
    );
  }
}
