#include "urma_1163_device_driver_interaction_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1163DeviceDriverInteractionFailure> g_urma("urma_1163");

bool Urma1163DeviceDriverInteractionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1164", "urma_1167", "urma_1170", "urma_1172",
                                                    "urma_1174", "urma_1177", "urma_1179"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1163DeviceDriverInteractionFailure::GetName() const
{
    return "设备/驱动交互失败";
}

std::string Urma1163DeviceDriverInteractionFailure::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause Urma1163DeviceDriverInteractionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1163DeviceDriverInteractionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1163DeviceDriverInteractionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1163DeviceDriverInteractionFailure::GetId() const
{
    return "urma_1163";
}
} // namespace diag
