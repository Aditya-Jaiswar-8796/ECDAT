/**
 * Root page — redirects straight to the dashboard overview.
 */
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/dashboard");
}