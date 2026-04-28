export const onRequestPost: PagesFunction = async ({ request }) => {
  try {
    await request.json();
  } catch {
    // Invalid JSON is ignored so the handler never throws.
  }

  return new Response(JSON.stringify({ success: true }), {
    headers: { "Content-Type": "application/json" },
  });
};
