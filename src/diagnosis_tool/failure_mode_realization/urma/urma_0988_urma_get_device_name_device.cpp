#include "urma_0988_urma_get_device_name_device.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0988UrmaGetDeviceNameDevice> g_urma("urma_0988");

bool Urma0988UrmaGetDeviceNameDevice::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"device list name:% does not match dev_name: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0988UrmaGetDeviceNameDevice::GetName() const
{
    return "urma_get_device_by_name 设备名称不匹配";
}

std::string Urma0988UrmaGetDeviceNameDevice::GetRootCauseDesc() const
{
    return "设备或资源查询失败，可能由于设备不存在、名称不匹配、设备能力不可用或下游查询返回错误；该路径返回 urma_dev";
}

RootCause Urma0988UrmaGetDeviceNameDevice::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0988UrmaGetDeviceNameDevice::GetFixSuggDesc() const
{
    return "```\nlsmod | grep udma\nurma_admin show -a // 查看UB设备是否存在，部署完成后重试\n```";
}

std::string Urma0988UrmaGetDeviceNameDevice::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：device list name:% does not match dev_name: %.";
}

std::string Urma0988UrmaGetDeviceNameDevice::GetId() const
{
    return "urma_0988";
}
} // namespace diag
