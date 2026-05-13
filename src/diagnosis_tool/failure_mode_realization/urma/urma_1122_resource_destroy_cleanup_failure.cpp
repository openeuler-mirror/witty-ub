#include "urma_1122_resource_destroy_cleanup_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1122ResourceDestroyCleanupFailure> g_urma("urma_1122");

bool Urma1122ResourceDestroyCleanupFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1123", "urma_1126", "urma_1128", "urma_1131", "urma_1135",
                                                    "urma_1137", "urma_1140", "urma_1142", "urma_1145", "urma_1148",
                                                    "urma_1150", "urma_1154", "urma_1156", "urma_1159", "urma_1161"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1122ResourceDestroyCleanupFailure::GetName() const
{
    return "资源销毁/清理失败";
}

std::string Urma1122ResourceDestroyCleanupFailure::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause Urma1122ResourceDestroyCleanupFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1122ResourceDestroyCleanupFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1122ResourceDestroyCleanupFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1122ResourceDestroyCleanupFailure::GetId() const
{
    return "urma_1122";
}
} // namespace diag
