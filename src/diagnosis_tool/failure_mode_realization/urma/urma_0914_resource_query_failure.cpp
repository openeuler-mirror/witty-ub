#include "urma_0914_resource_query_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0914ResourceQueryFailure> g_urma("urma_0914");

bool Urma0914ResourceQueryFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {
        "urma_0915", "urma_0918", "urma_0920", "urma_0924", "urma_0927", "urma_0929", "urma_0931",
        "urma_0935", "urma_0937", "urma_0939", "urma_0941", "urma_0943", "urma_0945", "urma_0947",
        "urma_0949", "urma_0951", "urma_0953", "urma_0955", "urma_0959", "urma_0961", "urma_0964",
        "urma_0968", "urma_0970", "urma_0972", "urma_0975", "urma_0977", "urma_0981", "urma_0983",
        "urma_0985", "urma_0989", "urma_0991", "urma_0993", "urma_0995"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0914ResourceQueryFailure::GetName() const
{
    return "资源查询失败";
}

std::string Urma0914ResourceQueryFailure::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause Urma0914ResourceQueryFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0914ResourceQueryFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0914ResourceQueryFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0914ResourceQueryFailure::GetId() const
{
    return "urma_0914";
}
} // namespace diag
