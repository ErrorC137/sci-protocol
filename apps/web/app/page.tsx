import { SiteFooter, SiteNav } from "@/components/SiteChrome";
import { Landing } from "@/components/landing/Landing";
import { MOTION_GATE } from "@/components/landing/motion-gate";
import { CapitalFlow } from "@/components/landing/sections/CapitalFlow";
import { Finale } from "@/components/landing/sections/Finale";
import { Gap } from "@/components/landing/sections/Gap";
import { Hero } from "@/components/landing/sections/Hero";
import { Pipeline } from "@/components/landing/sections/Pipeline";
import { Revenue } from "@/components/landing/sections/Revenue";
import { Trust } from "@/components/landing/sections/Trust";
import { TwoPools } from "@/components/landing/sections/TwoPools";

// "/" - the cinematic UPLO landing (docs/uplo, brief §3). Every section is real, server-rendered DOM text; motion
// and the 3D ring are progressive enhancements layered on top by <Landing>.
export default function Home() {
  return (
    <>
      <script dangerouslySetInnerHTML={{ __html: MOTION_GATE }} />
      <SiteNav />
      <Landing>
        <main>
          <Hero />
          <Gap />
          <CapitalFlow />
          <TwoPools />
          <Revenue />
          <Pipeline />
          <Trust />
          <Finale />
        </main>
      </Landing>
      <SiteFooter />
    </>
  );
}
