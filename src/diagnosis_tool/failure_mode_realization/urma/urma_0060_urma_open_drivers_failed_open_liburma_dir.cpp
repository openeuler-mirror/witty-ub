#include "urma_0060_urma_open_drivers_failed_open_liburma_dir.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0060UrmaOpenDriversFailedOpenLiburmaDir> g_urma("urma_0060");

bool Urma0060UrmaOpenDriversFailedOpenLiburmaDir::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to open liburma dir %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0060UrmaOpenDriversFailedOpenLiburmaDir::GetName() const
{
    return "urma_open_drivers Failed to open liburma dir %";
}

std::string Urma0060UrmaOpenDriversFailedOpenLiburmaDir::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 "
           "-1";
}

RootCause Urma0060UrmaOpenDriversFailedOpenLiburmaDir::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0060UrmaOpenDriversFailedOpenLiburmaDir::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0060UrmaOpenDriversFailedOpenLiburmaDir::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to open liburma dir %";
}

std::string Urma0060UrmaOpenDriversFailedOpenLiburmaDir::GetId() const
{
    return "urma_0060";
}
} // namespace diag
