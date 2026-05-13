#include "urma_0064_urma_open_provider_file_permission.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0064UrmaOpenProviderFilePermission> g_urma("urma_0064");

bool Urma0064UrmaOpenProviderFilePermission::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"% doesn't exist or doesn't have permission."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0064UrmaOpenProviderFilePermission::GetName() const
{
    return "urma_open_provider 文件不存在或权限不足";
}

std::string Urma0064UrmaOpenProviderFilePermission::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 "
           "-1";
}

RootCause Urma0064UrmaOpenProviderFilePermission::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0064UrmaOpenProviderFilePermission::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0064UrmaOpenProviderFilePermission::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：% doesn't exist or doesn't have permission.";
}

std::string Urma0064UrmaOpenProviderFilePermission::GetId() const
{
    return "urma_0064";
}
} // namespace diag
