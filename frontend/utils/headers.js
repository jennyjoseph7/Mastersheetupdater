// Environment-based URL: prod -> https://autobot-webapp-dev.gryd.in, test -> localhost:5008
const getAppBaseUrl = () => {
  let env = "test";
  let url = "http://localhost:5008";

  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    const isLocalhost = hostname === "localhost" || hostname === "127.0.0.1";
    const envOverride = process.env.NEXT_PUBLIC_APP_ENV;
    if (envOverride === "prod") {
      env = "prod";
      url = "http://localhost:5008";
    } else if (envOverride === "test") {
      env = "test";
      url = "http://localhost:5008";
    } else {
      if (isLocalhost) {
        env = "test";
        url = "http://localhost:5008";
      } else {
        env = "prod";
        url = "http://localhost:5008";
      }
    }
  } else {
    const envOverride = process.env.NEXT_PUBLIC_APP_ENV || process.env.APP_ENV;
    if (envOverride === "prod") {
      env = "prod";
      url = "http://localhost:5008";
    } else if (envOverride === "test") {
      env = "test";
      url = "http://localhost:5008";
    } else {
      if (process.env.NODE_ENV === "production") {
        env = "prod";
        url = "http://localhost:5008";
      } else {
        env = "test";
        url = "http://localhost:5008";
      }
    }
  }

  console.log(`[APP_ENV] Running in ${env.toUpperCase()} mode -> ${url}`);
  return url;
};

const APP_BASE_URL = getAppBaseUrl();

const HEADERS = {
  "Content-Type": "application/json",
  "X-GRYD-ENTERPRISE-ID": "autocrm",
  "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
  "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
  "X-GRYD-ROLE": "agent",
};

const FILE_UPLOAD_URL = "https://file-prod.gryd.in/media/document";
const FILE_UPLOAD_HEADERS = {
  "X-I2CE-ENTERPRISE-ID": "gryd_file_system",
  "X-I2CE-USER-ID": "abhishek+file-gryd@iamdave.ai",
  "X-I2CE-API-KEY": "4bd3fe53-02bf-3918-8e27-53095dd0e32b",
};

export { APP_BASE_URL, HEADERS, FILE_UPLOAD_URL, FILE_UPLOAD_HEADERS };
