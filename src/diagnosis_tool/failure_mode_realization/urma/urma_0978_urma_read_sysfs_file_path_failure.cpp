#include "urma_0978_urma_read_sysfs_file_path_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0978UrmaReadSysfsFilePathFailure> g_urma("urma_0978");

bool Urma0978UrmaReadSysfsFilePathFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"snprintf failed"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0978UrmaReadSysfsFilePathFailure::GetName() const
{
    return "urma_read_sysfs_file 格式化路径失败";
}

std::string Urma0978UrmaReadSysfsFilePathFailure::GetRootCauseDesc() const
{
    return "路径或字符串处理失败，可能由于缓冲区长度不足、输入名称异常或系统调用返回错误；该路径返回 -1";
}

RootCause Urma0978UrmaReadSysfsFilePathFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0978UrmaReadSysfsFilePathFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0978UrmaReadSysfsFilePathFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：snprintf failed";
}

std::string Urma0978UrmaReadSysfsFilePathFailure::GetId() const
{
    return "urma_0978";
}
} // namespace diag
