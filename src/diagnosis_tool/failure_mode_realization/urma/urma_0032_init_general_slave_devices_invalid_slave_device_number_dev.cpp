#include "urma_0032_init_general_slave_devices_invalid_slave_device_number_dev.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0032InitGeneralSlaveDevicesInvalidSlaveDeviceNumberDev> g_urma("urma_0032");

bool Urma0032InitGeneralSlaveDevicesInvalidSlaveDeviceNumberDev::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid slave device number % of device %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0032InitGeneralSlaveDevicesInvalidSlaveDeviceNumberDev::GetName() const
{
    return "init_general_slave_devices Invalid slave device number % of dev";
}

std::string Urma0032InitGeneralSlaveDevicesInvalidSlaveDeviceNumberDev::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_dev_num(dev_info.slave_dev_num)`；该路径返回 -1";
}

RootCause Urma0032InitGeneralSlaveDevicesInvalidSlaveDeviceNumberDev::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0032InitGeneralSlaveDevicesInvalidSlaveDeviceNumberDev::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0032InitGeneralSlaveDevicesInvalidSlaveDeviceNumberDev::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid slave device number % of device %";
}

std::string Urma0032InitGeneralSlaveDevicesInvalidSlaveDeviceNumberDev::GetId() const
{
    return "urma_0032";
}
} // namespace diag
