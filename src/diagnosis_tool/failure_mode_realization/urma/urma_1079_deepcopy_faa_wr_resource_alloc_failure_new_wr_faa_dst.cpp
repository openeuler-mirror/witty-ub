#include "urma_1079_deepcopy_faa_wr_resource_alloc_failure_new_wr_faa_dst.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1079DeepcopyFaaWrResourceAllocFailureNewWrFaaDst> g_urma("urma_1079");

bool Urma1079DeepcopyFaaWrResourceAllocFailureNewWrFaaDst::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc new_wr_faa->dst"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1079DeepcopyFaaWrResourceAllocFailureNewWrFaaDst::GetName() const
{
    return "deepcopy_faa_wr 分配资源失败（new_wr_faa->dst == NULL）";
}

std::string Urma1079DeepcopyFaaWrResourceAllocFailureNewWrFaaDst::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 -1";
}

RootCause Urma1079DeepcopyFaaWrResourceAllocFailureNewWrFaaDst::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1079DeepcopyFaaWrResourceAllocFailureNewWrFaaDst::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1079DeepcopyFaaWrResourceAllocFailureNewWrFaaDst::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc new_wr_faa->dst";
}

std::string Urma1079DeepcopyFaaWrResourceAllocFailureNewWrFaaDst::GetId() const
{
    return "urma_1079";
}
} // namespace diag
