#include "urma_failure_251.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure251> g_urma("urma_251");

bool UrmaFailure251::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jetty_check_dev_cap") != std::string::npos &&
           message.find("jetty_grp jetty cnt:") != std::string::npos &&
           message.find(", max_jetty in grp:") != std::string::npos;
}

std::string UrmaFailure251::GetName() const
{
    return "Jetty、设备、能力信息状态不满足要求导致创建Jetty、设备、能力信息失败";
}

std::string UrmaFailure251::GetRootCauseDesc() const
{
    return "urma_create_jetty_check_dev_"
           "cap执行创建Jetty、设备、能力信息时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure251::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure251::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure251::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_check_dev_cap，jetty_grp jetty cnt:，, max_jetty in "
           "grp:。";
}

std::string UrmaFailure251::GetId() const
{
    return "urma_251";
}
} // namespace diag
