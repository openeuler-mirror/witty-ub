#include "urma_0001_init_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0001InitFailure> g_urma("urma_0001");

bool Urma0001InitFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {
        "urma_0002", "urma_0005", "urma_0008", "urma_0011", "urma_0013", "urma_0015", "urma_0017", "urma_0019",
        "urma_0022", "urma_0026", "urma_0028", "urma_0030", "urma_0034", "urma_0040", "urma_0042", "urma_0046",
        "urma_0048", "urma_0051", "urma_0053", "urma_0056", "urma_0063", "urma_0067", "urma_0069"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0001InitFailure::GetName() const
{
    return "初始化失败";
}

std::string Urma0001InitFailure::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause Urma0001InitFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0001InitFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0001InitFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0001InitFailure::GetId() const
{
    return "urma_0001";
}
} // namespace diag
