#include "urma_failure_282.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure282> g_urma("urma_282");

bool UrmaFailure282::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_query_device") != std::string::npos &&
           message.find("Failed to query device attr, ret:") != std::string::npos;
}

std::string UrmaFailure282::GetName() const
{
    return "下层查询返回失败导致查询设备失败";
}

std::string UrmaFailure282::GetRootCauseDesc() const
{
    return "urma_query_device需要从provider、驱动或缓存中获取设备状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure282::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure282::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure282::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_device，Failed to query device attr, ret:。";
}

std::string UrmaFailure282::GetId() const
{
    return "urma_282";
}
} // namespace diag
