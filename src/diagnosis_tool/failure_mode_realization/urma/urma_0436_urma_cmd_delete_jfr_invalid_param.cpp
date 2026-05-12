#include "urma_0436_urma_cmd_delete_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0436UrmaCmdDeleteJfrInvalidParam> g_urma("urma_0436");

bool Urma0436UrmaCmdDeleteJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0436UrmaCmdDeleteJfrInvalidParam::GetName() const
{
    return "urma_cmd_delete_jfr 参数非法";
}

std::string Urma0436UrmaCmdDeleteJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL || jfr->urma_ctx == NULL || jfr->urma_ctx->dev_fd < "
           "0`；该路径返回 -1";
}

RootCause Urma0436UrmaCmdDeleteJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0436UrmaCmdDeleteJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0436UrmaCmdDeleteJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0436UrmaCmdDeleteJfrInvalidParam::GetId() const
{
    return "urma_0436";
}
} // namespace diag
