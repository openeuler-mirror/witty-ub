#include "urma_0979_urma_read_sysfs_file_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0979UrmaReadSysfsFileFailure> g_urma("urma_0979");

bool Urma0979UrmaReadSysfsFileFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed open file: %, errno: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0979UrmaReadSysfsFileFailure::GetName() const
{
    return "urma_read_sysfs_file 打开文件失败";
}

std::string Urma0979UrmaReadSysfsFileFailure::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 "
           "-1";
}

RootCause Urma0979UrmaReadSysfsFileFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0979UrmaReadSysfsFileFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0979UrmaReadSysfsFileFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed open file: %, errno: %.";
}

std::string Urma0979UrmaReadSysfsFileFailure::GetId() const
{
    return "urma_0979";
}
} // namespace diag
