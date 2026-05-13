#include "urma_1081_deepcopy_faa_wr_resource_alloc_failure_new_wr_faa_src.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1081DeepcopyFaaWrResourceAllocFailureNewWrFaaSrc> g_urma("urma_1081");

bool Urma1081DeepcopyFaaWrResourceAllocFailureNewWrFaaSrc::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc new_wr_faa->src"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1081DeepcopyFaaWrResourceAllocFailureNewWrFaaSrc::GetName() const
{
    return "deepcopy_faa_wr 分配资源失败（new_wr_faa->src == NULL）";
}

std::string Urma1081DeepcopyFaaWrResourceAllocFailureNewWrFaaSrc::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制";
}

RootCause Urma1081DeepcopyFaaWrResourceAllocFailureNewWrFaaSrc::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1081DeepcopyFaaWrResourceAllocFailureNewWrFaaSrc::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1081DeepcopyFaaWrResourceAllocFailureNewWrFaaSrc::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc new_wr_faa->src";
}

std::string Urma1081DeepcopyFaaWrResourceAllocFailureNewWrFaaSrc::GetId() const
{
    return "urma_1081";
}
} // namespace diag
