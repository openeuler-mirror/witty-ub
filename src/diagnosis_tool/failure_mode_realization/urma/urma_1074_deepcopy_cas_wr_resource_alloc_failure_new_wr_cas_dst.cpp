#include "urma_1074_deepcopy_cas_wr_resource_alloc_failure_new_wr_cas_dst.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1074DeepcopyCasWrResourceAllocFailureNewWrCasDst> g_urma("urma_1074");

bool Urma1074DeepcopyCasWrResourceAllocFailureNewWrCasDst::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc new_wr_cas->dst"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1074DeepcopyCasWrResourceAllocFailureNewWrCasDst::GetName() const
{
    return "deepcopy_cas_wr 分配资源失败（new_wr_cas->dst == NULL）";
}

std::string Urma1074DeepcopyCasWrResourceAllocFailureNewWrCasDst::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 -1";
}

RootCause Urma1074DeepcopyCasWrResourceAllocFailureNewWrCasDst::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1074DeepcopyCasWrResourceAllocFailureNewWrCasDst::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1074DeepcopyCasWrResourceAllocFailureNewWrCasDst::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc new_wr_cas->dst";
}

std::string Urma1074DeepcopyCasWrResourceAllocFailureNewWrCasDst::GetId() const
{
    return "urma_1074";
}
} // namespace diag
