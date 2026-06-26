#include "urma_failure_147.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure147> g_urma("urma_147");

bool UrmaFailure147::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jetty") != std::string::npos &&
           message.find("Invalid well known jetty id:") != std::string::npos &&
           message.find(", should be in (0, 1024)") != std::string::npos;
}

std::string UrmaFailure147::GetName() const
{
    return "Jetty状态不满足要求导致创建Jetty失败";
}

std::string UrmaFailure147::GetRootCauseDesc() const
{
    return "bondp_create_jetty执行创建Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure147::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure147::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure147::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jetty，Invalid well known jetty id:，, should be in (0, "
           "1024)。";
}

std::string UrmaFailure147::GetId() const
{
    return "urma_147";
}
} // namespace diag
