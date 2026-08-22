export const runtime = "edge"

export async function GET() {
  return new Response(
    JSON.stringify({
      status: "ok",
      service: "frontend",
      timestamp: new Date().toISOString(),
    }),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
      },
    }
  )
}

export async function HEAD() {
  return new Response(null, {
    status: 200,
    headers: {
      "Cache-Control": "no-store",
    },
  })
}

