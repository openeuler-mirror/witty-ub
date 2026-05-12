#include "urma_0888_resource_creation_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0888ResourceCreationFailure> g_urma("urma_0888");

bool Urma0888ResourceCreationFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0889", "urma_0891", "urma_0894", "urma_0896", "urma_0900",
                                                    "urma_0903", "urma_0905", "urma_0907", "urma_0909"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0888ResourceCreationFailure::GetName() const
{
    return "资源创建失败";
}

std::string Urma0888ResourceCreationFailure::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause Urma0888ResourceCreationFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0888ResourceCreationFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0888ResourceCreationFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0888ResourceCreationFailure::GetId() const
{
    return "urma_0888";
}
} // namespace diag
