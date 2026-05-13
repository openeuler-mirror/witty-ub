#include "urma_0997_urma_query_device_query_device_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0997UrmaQueryDeviceQueryDeviceFailure> g_urma("urma_0997");

bool Urma0997UrmaQueryDeviceQueryDeviceFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to query device attr, ret: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0997UrmaQueryDeviceQueryDeviceFailure::GetName() const
{
    return "urma_query_device 查询设备属性失败";
}

std::string Urma0997UrmaQueryDeviceQueryDeviceFailure::GetRootCauseDesc() const
{
    return "设备或资源查询失败，可能由于设备不存在、名称不匹配、设备能力不可用或下游查询返回错误；该路径返回 URMA_FAIL";
}

RootCause Urma0997UrmaQueryDeviceQueryDeviceFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0997UrmaQueryDeviceQueryDeviceFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0997UrmaQueryDeviceQueryDeviceFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to query device attr, ret: %.";
}

std::string Urma0997UrmaQueryDeviceQueryDeviceFailure::GetId() const
{
    return "urma_0997";
}
} // namespace diag
