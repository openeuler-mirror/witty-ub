#include "urma_failure_656.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure656> g_urma("urma_656");

bool UrmaFailure656::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_parse_rsvd_jetty_range") != std::string::npos &&
           message.find("parse sysfs:") != std::string::npos && message.find("failed") != std::string::npos;
}

std::string UrmaFailure656::GetName() const
{
    return "sysfs路径信息读取或解析失败导致解析RSVD、Jetty、range失败";
}

std::string UrmaFailure656::GetRootCauseDesc() const
{
    return "urma_parse_rsvd_jetty_"
           "range需要从sysfs获取sysfs路径信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure656::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure656::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure656::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_parse_rsvd_jetty_range，parse sysfs:，failed。";
}

std::string UrmaFailure656::GetId() const
{
    return "urma_656";
}
} // namespace diag
