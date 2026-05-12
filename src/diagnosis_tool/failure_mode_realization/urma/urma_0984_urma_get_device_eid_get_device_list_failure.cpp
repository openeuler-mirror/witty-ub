#include "urma_0984_urma_get_device_eid_get_device_list_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0984UrmaGetDeviceEidGetDeviceListFailure> g_urma("urma_0984");

bool Urma0984UrmaGetDeviceEidGetDeviceListFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"urma get device list failed!"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0984UrmaGetDeviceEidGetDeviceListFailure::GetName() const
{
    return "urma_get_device_by_eid 获取设备列表失败";
}

std::string Urma0984UrmaGetDeviceEidGetDeviceListFailure::GetRootCauseDesc() const
{
    return "设备或资源查询失败，可能由于设备不存在、名称不匹配、设备能力不可用或下游查询返回错误；该路径返回 NULL";
}

RootCause Urma0984UrmaGetDeviceEidGetDeviceListFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0984UrmaGetDeviceEidGetDeviceListFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0984UrmaGetDeviceEidGetDeviceListFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：urma get device list failed!";
}

std::string Urma0984UrmaGetDeviceEidGetDeviceListFailure::GetId() const
{
    return "urma_0984";
}
} // namespace diag
