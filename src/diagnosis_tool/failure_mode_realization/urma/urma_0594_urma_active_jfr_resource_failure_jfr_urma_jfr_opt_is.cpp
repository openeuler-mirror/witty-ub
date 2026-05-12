#include "urma_0594_urma_active_jfr_resource_failure_jfr_urma_jfr_opt_is.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0594UrmaActiveJfrResourceFailureJfrUrmaJfrOptIs> g_urma("urma_0594");

bool Urma0594UrmaActiveJfrResourceFailureJfrUrmaJfrOptIs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfr state is wrong in active_jfr."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0594UrmaActiveJfrResourceFailureJfrUrmaJfrOptIs::GetName() const
{
    return "urma_active_jfr 激活资源失败（jfr->urma_jfr_opt.is_actived == true）";
}

std::string Urma0594UrmaActiveJfrResourceFailureJfrUrmaJfrOptIs::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0594UrmaActiveJfrResourceFailureJfrUrmaJfrOptIs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0594UrmaActiveJfrResourceFailureJfrUrmaJfrOptIs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0594UrmaActiveJfrResourceFailureJfrUrmaJfrOptIs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfr state is wrong in active_jfr.";
}

std::string Urma0594UrmaActiveJfrResourceFailureJfrUrmaJfrOptIs::GetId() const
{
    return "urma_0594";
}
} // namespace diag
