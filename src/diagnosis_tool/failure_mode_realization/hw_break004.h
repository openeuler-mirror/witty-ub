#pragma once

#include "../failure_mode.h"
namespace diag {
class HwBreak004 : public FailureMode {
public:
    bool IsValid() override;
    std::string GetName() const override;
    std::string GetRootCauseDesc() const override;
    std::string GetFixSuggDesc() const override;
    std::string GetValidationMethodDesc() const override;
    std::string GetId() const override;
};
}