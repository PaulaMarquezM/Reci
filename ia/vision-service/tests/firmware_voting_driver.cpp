#include <iostream>

#include "../../../firmware/esp32-cam/ReciEsp32Cam/VisionVotingPolicy.h"

int main() {
  unsigned int providerPlastic = 0;
  unsigned int providerGlass = 0;
  unsigned int providerAbstentions = 0;
  unsigned int localPlastic = 0;
  unsigned int localGlass = 0;
  unsigned int localAbstentions = 0;
  unsigned int complete = 0;

  while (std::cin >> providerPlastic >> providerGlass >> providerAbstentions >>
         localPlastic >> localGlass >> localAbstentions >> complete) {
    const reci_vision::VoteCounts provider{
        static_cast<uint8_t>(providerPlastic),
        static_cast<uint8_t>(providerGlass),
        static_cast<uint8_t>(providerAbstentions)};
    const reci_vision::VoteCounts local{
        static_cast<uint8_t>(localPlastic),
        static_cast<uint8_t>(localGlass),
        static_cast<uint8_t>(localAbstentions)};
    const reci_vision::Decision decision =
        reci_vision::decide(provider, local, complete != 0);

    std::cout << reci_vision::materialName(decision.material) << '|'
              << reci_vision::sourceName(decision.source) << '|'
              << (reci_vision::shouldSendClassify(decision) ? "CMD" : "NO_CMD")
              << '\n';
  }
  return 0;
}
