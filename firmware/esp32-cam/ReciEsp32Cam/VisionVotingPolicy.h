#ifndef RECI_VISION_VOTING_POLICY_H
#define RECI_VISION_VOTING_POLICY_H

#include <stdint.h>

namespace reci_vision {

enum class Material : uint8_t {
  Desconocido,
  Plastico,
  Vidrio,
};

enum class DecisionSource : uint8_t {
  RespuestaIncompleta,
  ModeloLocalUnanime,
  ModeloLocalNoUnanime,
  VotacionConjunta,
  DesempateOpenaiSistemaExperto,
  ConfusionSinResolver,
};

struct VoteCounts {
  uint8_t plastico;
  uint8_t vidrio;
  uint8_t abstenciones;
};

struct Decision {
  Material material;
  DecisionSource source;
};

inline Decision decide(const VoteCounts& provider,
                       const VoteCounts& local,
                       bool capturesComplete,
                       uint8_t expectedCaptures = 3) {
  const uint8_t providerCount =
      provider.plastico + provider.vidrio + provider.abstenciones;
  const uint8_t localCount = local.plastico + local.vidrio + local.abstenciones;

  // El modelo local desplegado es binario. Una abstención local, una cantidad
  // distinta de diagnósticos o una captura fallida invalidan el depósito.
  if (!capturesComplete || providerCount != expectedCaptures ||
      localCount != expectedCaptures || local.abstenciones != 0) {
    return {Material::Desconocido, DecisionSource::RespuestaIncompleta};
  }

  const uint8_t providerValid = provider.plastico + provider.vidrio;
  if (providerValid == 0) {
    if (local.plastico == expectedCaptures) {
      return {Material::Plastico, DecisionSource::ModeloLocalUnanime};
    }
    if (local.vidrio == expectedCaptures) {
      return {Material::Vidrio, DecisionSource::ModeloLocalUnanime};
    }
    return {Material::Desconocido, DecisionSource::ModeloLocalNoUnanime};
  }

  const uint8_t totalPlastic = provider.plastico + local.plastico;
  const uint8_t totalGlass = provider.vidrio + local.vidrio;
  if (totalPlastic > totalGlass) {
    return {Material::Plastico, DecisionSource::VotacionConjunta};
  }
  if (totalGlass > totalPlastic) {
    return {Material::Vidrio, DecisionSource::VotacionConjunta};
  }

  if (provider.plastico > provider.vidrio) {
    return {Material::Plastico,
            DecisionSource::DesempateOpenaiSistemaExperto};
  }
  if (provider.vidrio > provider.plastico) {
    return {Material::Vidrio,
            DecisionSource::DesempateOpenaiSistemaExperto};
  }
  return {Material::Desconocido, DecisionSource::ConfusionSinResolver};
}

inline bool shouldSendClassify(const Decision& decision) {
  return decision.material == Material::Plastico ||
         decision.material == Material::Vidrio;
}

inline bool usesProviderTieBreak(const Decision& decision) {
  return decision.source == DecisionSource::DesempateOpenaiSistemaExperto;
}

inline const char* materialName(Material material) {
  if (material == Material::Plastico) return "plastico";
  if (material == Material::Vidrio) return "vidrio";
  return "desconocido";
}

inline const char* sourceName(DecisionSource source) {
  switch (source) {
    case DecisionSource::ModeloLocalUnanime:
      return "modelo_local_unanime";
    case DecisionSource::ModeloLocalNoUnanime:
      return "modelo_local_no_unanime";
    case DecisionSource::VotacionConjunta:
      return "votacion_conjunta";
    case DecisionSource::DesempateOpenaiSistemaExperto:
      return "desempate_openai_sistema_experto";
    case DecisionSource::ConfusionSinResolver:
      return "confusion_sin_resolver";
    case DecisionSource::RespuestaIncompleta:
    default:
      return "respuesta_incompleta";
  }
}

}  // namespace reci_vision

#endif  // RECI_VISION_VOTING_POLICY_H
