#include "urma_0396_urma_cmd_create_jfs_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0396UrmaCmdCreateJfsInvalidParam> g_urma("urma_0396");

bool Urma0396UrmaCmdCreateJfsInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0396UrmaCmdCreateJfsInvalidParam::GetName() const
{
    return "urma_cmd_create_jfs 参数非法";
}

std::string Urma0396UrmaCmdCreateJfsInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || jfs == NULL || cfg == NULL || cfg->jfc == "
           "NULL`；该路径返回 -1";
}

RootCause Urma0396UrmaCmdCreateJfsInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0396UrmaCmdCreateJfsInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0396UrmaCmdCreateJfsInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0396UrmaCmdCreateJfsInvalidParam::GetId() const
{
    return "urma_0396";
}
} // namespace diag
