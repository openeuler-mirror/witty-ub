#include "urma_failure_146.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure146> g_urma("urma_146");

bool UrmaFailure146::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jetty") != std::string::npos &&
           message.find("UB device must use shared jfr when create jetty.") != std::string::npos;
}

std::string UrmaFailure146::GetName() const
{
    return "Jetty状态不满足要求导致创建Jetty失败";
}

std::string UrmaFailure146::GetRootCauseDesc() const
{
    return "bondp_create_jetty执行创建Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure146::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure146::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure146::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jetty，UB device must use shared jfr when create jetty.。";
}

std::string UrmaFailure146::GetId() const
{
    return "urma_146";
}
} // namespace diag
