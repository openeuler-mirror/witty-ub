#include "urma_1076_deepcopy_cas_wr_resource_alloc_failure_new_wr_cas_src.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1076DeepcopyCasWrResourceAllocFailureNewWrCasSrc> g_urma("urma_1076");

bool Urma1076DeepcopyCasWrResourceAllocFailureNewWrCasSrc::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc new_wr_cas->src"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1076DeepcopyCasWrResourceAllocFailureNewWrCasSrc::GetName() const
{
    return "deepcopy_cas_wr 分配资源失败（new_wr_cas->src == NULL）";
}

std::string Urma1076DeepcopyCasWrResourceAllocFailureNewWrCasSrc::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制";
}

RootCause Urma1076DeepcopyCasWrResourceAllocFailureNewWrCasSrc::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1076DeepcopyCasWrResourceAllocFailureNewWrCasSrc::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1076DeepcopyCasWrResourceAllocFailureNewWrCasSrc::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc new_wr_cas->src";
}

std::string Urma1076DeepcopyCasWrResourceAllocFailureNewWrCasSrc::GetId() const
{
    return "urma_1076";
}
} // namespace diag
