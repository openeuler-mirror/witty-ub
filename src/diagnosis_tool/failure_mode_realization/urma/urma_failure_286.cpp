#include "urma_failure_286.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure286> g_urma("urma_286");

bool UrmaFailure286::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_device_by_eid") != std::string::npos &&
           message.find("urma get device list failed!") != std::string::npos;
}

std::string UrmaFailure286::GetName() const
{
    return "下层查询返回失败导致获取设备、EID失败";
}

std::string UrmaFailure286::GetRootCauseDesc() const
{
    return "urma_get_device_by_"
           "eid需要从provider、驱动或缓存中获取设备、EID状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure286::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure286::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure286::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_device_by_eid，urma get device list failed!。";
}

std::string UrmaFailure286::GetId() const
{
    return "urma_286";
}
} // namespace diag
