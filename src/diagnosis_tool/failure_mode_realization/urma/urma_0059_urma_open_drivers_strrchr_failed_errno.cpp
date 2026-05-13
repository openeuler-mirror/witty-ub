#include "urma_0059_urma_open_drivers_strrchr_failed_errno.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0059UrmaOpenDriversStrrchrFailedErrno> g_urma("urma_0059");

bool Urma0059UrmaOpenDriversStrrchrFailedErrno::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"strrchr % failed, errno: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0059UrmaOpenDriversStrrchrFailedErrno::GetName() const
{
    return "urma_open_drivers strrchr % failed, errno: %";
}

std::string Urma0059UrmaOpenDriversStrrchrFailedErrno::GetRootCauseDesc() const
{
    return "路径或字符串处理失败，可能由于缓冲区长度不足、输入名称异常或系统调用返回错误；该路径返回 -1";
}

RootCause Urma0059UrmaOpenDriversStrrchrFailedErrno::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0059UrmaOpenDriversStrrchrFailedErrno::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0059UrmaOpenDriversStrrchrFailedErrno::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：strrchr % failed, errno: %";
}

std::string Urma0059UrmaOpenDriversStrrchrFailedErrno::GetId() const
{
    return "urma_0059";
}
} // namespace diag
