#include "urma_0035_init_matrix_slave_devices_get_device_list_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0035InitMatrixSlaveDevicesGetDeviceListFailure> g_urma("urma_0035");

bool Urma0035InitMatrixSlaveDevicesGetDeviceListFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"urma get device list failed!"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0035InitMatrixSlaveDevicesGetDeviceListFailure::GetName() const
{
    return "init_matrix_slave_devices 获取设备列表失败";
}

std::string Urma0035InitMatrixSlaveDevicesGetDeviceListFailure::GetRootCauseDesc() const
{
    return "设备或资源查询失败，可能由于设备不存在、名称不匹配、设备能力不可用或下游查询返回错误；该路径返回 -1";
}

RootCause Urma0035InitMatrixSlaveDevicesGetDeviceListFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0035InitMatrixSlaveDevicesGetDeviceListFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0035InitMatrixSlaveDevicesGetDeviceListFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：urma get device list failed!";
}

std::string Urma0035InitMatrixSlaveDevicesGetDeviceListFailure::GetId() const
{
    return "urma_0035";
}
} // namespace diag
