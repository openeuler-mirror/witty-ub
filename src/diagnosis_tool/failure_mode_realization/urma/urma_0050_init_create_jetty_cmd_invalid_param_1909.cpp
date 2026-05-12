#include "urma_0050_init_create_jetty_cmd_invalid_param_1909.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0050InitCreateJettyCmdInvalidParam1909> g_urma("urma_0050");

bool Urma0050InitCreateJettyCmdInvalidParam1909::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0050InitCreateJettyCmdInvalidParam1909::GetName() const
{
    return "init_create_jetty_cmd 参数非法（日志行1909）";
}

std::string Urma0050InitCreateJettyCmdInvalidParam1909::GetRootCauseDesc() const
{
    return "函数参数校验失败；该路径返回 -1";
}

RootCause Urma0050InitCreateJettyCmdInvalidParam1909::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0050InitCreateJettyCmdInvalidParam1909::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0050InitCreateJettyCmdInvalidParam1909::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0050InitCreateJettyCmdInvalidParam1909::GetId() const
{
    return "urma_0050";
}
} // namespace diag
