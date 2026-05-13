#include "urma_1010_bondp_register_seg_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1010BondpRegisterSegResourceAllocFailure> g_urma("urma_1010");

bool Urma1010BondpRegisterSegResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc bondp segment comp"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1010BondpRegisterSegResourceAllocFailure::GetName() const
{
    return "bondp_register_seg 分配资源失败";
}

std::string Urma1010BondpRegisterSegResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 NULL";
}

RootCause Urma1010BondpRegisterSegResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1010BondpRegisterSegResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1010BondpRegisterSegResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc bondp segment comp";
}

std::string Urma1010BondpRegisterSegResourceAllocFailure::GetId() const
{
    return "urma_1010";
}
} // namespace diag
