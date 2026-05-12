#include "urma_0987_urma_get_device_name_get_device_list_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0987UrmaGetDeviceNameGetDeviceListFailure> g_urma("urma_0987");

bool Urma0987UrmaGetDeviceNameGetDeviceListFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"urma get device list failed, device_num: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0987UrmaGetDeviceNameGetDeviceListFailure::GetName() const
{
    return "urma_get_device_by_name 获取设备列表失败";
}

std::string Urma0987UrmaGetDeviceNameGetDeviceListFailure::GetRootCauseDesc() const
{
    return "设备或资源查询失败，可能由于设备不存在、名称不匹配、设备能力不可用或下游查询返回错误；该路径返回 NULL";
}

RootCause Urma0987UrmaGetDeviceNameGetDeviceListFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0987UrmaGetDeviceNameGetDeviceListFailure::GetFixSuggDesc() const
{
    return "```\nlsmod | grep udma\nurma_admin show -a // 查看UB设备是否存在，部署完成后重试\n```";
}

std::string Urma0987UrmaGetDeviceNameGetDeviceListFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：urma get device list failed, device_num: %.";
}

std::string Urma0987UrmaGetDeviceNameGetDeviceListFailure::GetId() const
{
    return "urma_0987";
}
} // namespace diag
