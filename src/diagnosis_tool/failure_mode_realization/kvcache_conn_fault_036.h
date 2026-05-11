#pragma once

#include "../failure_mode.h"
namespace diag {
class KvcacheConnFault036 : public FailureMode {
public:
    KvcacheConnFault036() noexcept;
    bool IsValid() override;
    std::string GetName() const override;
    std::string GetRootCauseDesc() const override;
    RootCause AnalyzeRootCause() override;
    std::string GetFixSuggDesc() const override;
    std::string GetValidationMethodDesc() const override;
    std::string GetId() const override;
};
}