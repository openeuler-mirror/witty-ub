#include "urma_failure_657.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure657> g_urma("urma_657");

bool UrmaFailure657::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_parse_rsvd_jetty_range") != std::string::npos &&
           message.find("parse rsvd jetty:") != std::string::npos && message.find("failed") != std::string::npos;
}

std::string UrmaFailure657::GetName() const
{
    return "设备端口信息读取或解析失败导致解析RSVD、Jetty、range失败";
}

std::string UrmaFailure657::GetRootCauseDesc() const
{
    return "urma_parse_rsvd_jetty_"
           "range需要从sysfs获取设备端口信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure657::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure657::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure657::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_parse_rsvd_jetty_range，parse rsvd jetty:，failed。";
}

std::string UrmaFailure657::GetId() const
{
    return "urma_657";
}
} // namespace diag
