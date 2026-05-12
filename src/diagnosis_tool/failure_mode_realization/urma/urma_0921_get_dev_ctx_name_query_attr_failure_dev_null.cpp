#include "urma_0921_get_dev_ctx_name_query_attr_failure_dev_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0921GetDevCtxNameQueryAttrFailureDevNull> g_urma("urma_0921");

bool Urma0921GetDevCtxNameQueryAttrFailureDevNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to get device"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0921GetDevCtxNameQueryAttrFailureDevNull::GetName() const
{
    return "get_dev_and_ctx_by_name 查询属性失败（*dev == NULL）";
}

std::string Urma0921GetDevCtxNameQueryAttrFailureDevNull::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `*dev == NULL`；该路径返回 -1";
}

RootCause Urma0921GetDevCtxNameQueryAttrFailureDevNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0921GetDevCtxNameQueryAttrFailureDevNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0921GetDevCtxNameQueryAttrFailureDevNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to get device";
}

std::string Urma0921GetDevCtxNameQueryAttrFailureDevNull::GetId() const
{
    return "urma_0921";
}
} // namespace diag
