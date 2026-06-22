#include "urma_failure_597.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure597> g_urma("urma_597");

bool UrmaFailure597::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_deactive_jetty") != std::string::npos &&
           message.find("Jetty state is wrong in deactive_jetty.") != std::string::npos;
}

std::string UrmaFailure597::GetName() const
{
    return "Jetty状态不满足要求导致去激活Jetty失败";
}

std::string UrmaFailure597::GetRootCauseDesc() const
{
    return "urma_deactive_jetty执行去激活Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure597::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure597::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure597::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jetty，Jetty state is wrong in deactive_jetty.。";
}

std::string UrmaFailure597::GetId() const
{
    return "urma_597";
}
} // namespace diag
