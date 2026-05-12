#include "urma_0360_urma_cmd_advise_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0360UrmaCmdAdviseJfrInvalidParam> g_urma("urma_0360");

bool Urma0360UrmaCmdAdviseJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0360UrmaCmdAdviseJfrInvalidParam::GetName() const
{
    return "urma_cmd_advise_jfr 参数非法";
}

std::string Urma0360UrmaCmdAdviseJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL || jfs->urma_ctx == NULL || jfs->urma_ctx->dev_fd < 0 || tjfr == "
           "NULL`；该路径返回 -1";
}

RootCause Urma0360UrmaCmdAdviseJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0360UrmaCmdAdviseJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0360UrmaCmdAdviseJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0360UrmaCmdAdviseJfrInvalidParam::GetId() const
{
    return "urma_0360";
}
} // namespace diag
