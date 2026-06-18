#include "urma_failure_471.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure471> g_urma("urma_471");

bool UrmaFailure471::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_deactive_jfc") != std::string::npos &&
           message.find("Jfc state is wrong in deactive_jfc.") != std::string::npos;
}

std::string UrmaFailure471::GetName() const
{
    return "JFC状态不满足要求导致去激活JFC失败";
}

std::string UrmaFailure471::GetRootCauseDesc() const
{
    return "urma_deactive_jfc执行去激活JFC时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure471::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure471::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure471::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfc，Jfc state is wrong in deactive_jfc.。";
}

std::string UrmaFailure471::GetId() const
{
    return "urma_471";
}
} // namespace diag
