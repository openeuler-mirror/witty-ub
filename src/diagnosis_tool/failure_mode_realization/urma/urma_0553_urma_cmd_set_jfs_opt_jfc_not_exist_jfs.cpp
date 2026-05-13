#include "urma_0553_urma_cmd_set_jfs_opt_jfc_not_exist_jfs.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0553UrmaCmdSetJfsOptJfcNotExistJfs> g_urma("urma_0553");

bool Urma0553UrmaCmdSetJfsOptJfcNotExistJfs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfc not exist in jfs."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0553UrmaCmdSetJfsOptJfcNotExistJfs::GetName() const
{
    return "urma_cmd_set_jfs_opt jfc not exist in jfs.";
}

std::string Urma0553UrmaCmdSetJfsOptJfcNotExistJfs::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 "
           "-1";
}

RootCause Urma0553UrmaCmdSetJfsOptJfcNotExistJfs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0553UrmaCmdSetJfsOptJfcNotExistJfs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0553UrmaCmdSetJfsOptJfcNotExistJfs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfc not exist in jfs.";
}

std::string Urma0553UrmaCmdSetJfsOptJfcNotExistJfs::GetId() const
{
    return "urma_0553";
}
} // namespace diag
