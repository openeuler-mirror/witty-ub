#include "urma_0393_urma_cmd_create_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0393UrmaCmdCreateJfrInvalidParam> g_urma("urma_0393");

bool Urma0393UrmaCmdCreateJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0393UrmaCmdCreateJfrInvalidParam::GetName() const
{
    return "urma_cmd_create_jfr 参数非法";
}

std::string Urma0393UrmaCmdCreateJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || jfr == NULL || cfg == NULL || cfg->jfc == "
           "NULL`；该路径返回 -1";
}

RootCause Urma0393UrmaCmdCreateJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0393UrmaCmdCreateJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0393UrmaCmdCreateJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0393UrmaCmdCreateJfrInvalidParam::GetId() const
{
    return "urma_0393";
}
} // namespace diag
