// src/pages/auth/VerifyEmailPage.tsx
import { useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { verifyEmail } from "../../auth/auth.api";
import { AuthLayout } from "./AuthLayout";

export function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token");

  const mutation = useMutation({
    mutationFn: () => {
      if (!token) throw new Error("Missing token");
      return verifyEmail(token);
    },
  });

  useEffect(() => {
    mutation.mutate();
  }, []);

  return (
    <AuthLayout>
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-8 shadow-lg">
        <div className="text-xl font-semibold">Email verification</div>
        <div className="mt-1 text-sm text-zinc-400">
          Validating your account.
        </div>

        <div className="mt-6 text-sm">
          {mutation.isPending && "Verifying…"}
          {mutation.isError && "Verification failed."}
          {mutation.isSuccess && mutation.data.message}
        </div>

        <Link
          to="/login"
          className="mt-6 inline-flex rounded-lg bg-white/90 px-4 py-2 text-sm font-semibold text-zinc-950 hover:bg-white"
        >
          Go to login
        </Link>
      </div>
    </AuthLayout>
  );
}
