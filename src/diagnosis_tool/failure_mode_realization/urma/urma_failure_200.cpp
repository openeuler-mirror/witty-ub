#include "urma_failure_200.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure200> g_urma("urma_200");

bool UrmaFailure200::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jetty_check_trans_mode") != std::string::npos &&
           message.find("UB dev should use share jfr!") != std::string::npos;
}

std::string UrmaFailure200::GetName() const
{
    return "Jetty、trans、MODE状态不满足要求导致创建Jetty、trans、MODE失败";
}

std::string UrmaFailure200::GetRootCauseDesc() const
{
    return "urma_create_jetty_check_trans_"
           "mode执行创建Jetty、trans、MODE时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure200::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure200::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure200::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_check_trans_mode，UB dev should use share jfr!。";
}

std::string UrmaFailure200::GetId() const
{
    return "urma_200";
}
} // namespace diag
