#include "urma_0058_urma_open_drivers_failed_prepare_dli_fname.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0058UrmaOpenDriversFailedPrepareDliFname> g_urma("urma_0058");

bool Urma0058UrmaOpenDriversFailedPrepareDliFname::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to prepare dli_fname."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0058UrmaOpenDriversFailedPrepareDliFname::GetName() const
{
    return "urma_open_drivers Failed to prepare dli_fname.";
}

std::string Urma0058UrmaOpenDriversFailedPrepareDliFname::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `snprintf(dl_dir, URMA_MAX_LIB_PATH, \"%\", info.dli_fname) <= 0`；该路径返回 -1";
}

RootCause Urma0058UrmaOpenDriversFailedPrepareDliFname::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0058UrmaOpenDriversFailedPrepareDliFname::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0058UrmaOpenDriversFailedPrepareDliFname::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to prepare dli_fname.";
}

std::string Urma0058UrmaOpenDriversFailedPrepareDliFname::GetId() const
{
    return "urma_0058";
}
} // namespace diag
