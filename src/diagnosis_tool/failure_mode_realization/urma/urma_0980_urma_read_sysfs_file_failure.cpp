#include "urma_0980_urma_read_sysfs_file_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0980UrmaReadSysfsFileFailure> g_urma("urma_0980");

bool Urma0980UrmaReadSysfsFileFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed read file: %, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0980UrmaReadSysfsFileFailure::GetName() const
{
    return "urma_read_sysfs_file 读取文件失败";
}

std::string Urma0980UrmaReadSysfsFileFailure::GetRootCauseDesc() const
{
    return "读取 sysfs 或设备文件失败，可能由于设备未注册、路径不存在、权限不足或读取返回异常；该路径返回 -1";
}

RootCause Urma0980UrmaReadSysfsFileFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0980UrmaReadSysfsFileFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0980UrmaReadSysfsFileFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed read file: %, ret:%, errno:%.";
}

std::string Urma0980UrmaReadSysfsFileFailure::GetId() const
{
    return "urma_0980";
}
} // namespace diag
