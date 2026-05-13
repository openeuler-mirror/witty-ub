#include "urma_0405_urma_cmd_deactive_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0405UrmaCmdDeactiveJfrInvalidParam> g_urma("urma_0405");

bool Urma0405UrmaCmdDeactiveJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0405UrmaCmdDeactiveJfrInvalidParam::GetName() const
{
    return "urma_cmd_deactive_jfr 参数非法";
}

std::string Urma0405UrmaCmdDeactiveJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL || jfr->urma_ctx == NULL || jfr->urma_ctx->dev_fd < "
           "0`；该路径返回 -1";
}

RootCause Urma0405UrmaCmdDeactiveJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0405UrmaCmdDeactiveJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0405UrmaCmdDeactiveJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0405UrmaCmdDeactiveJfrInvalidParam::GetId() const
{
    return "urma_0405";
}
} // namespace diag
