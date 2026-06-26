#include "kvcache_conn_fault_002.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault002> g_kvcacheconnfault("kvcache_conn_fault_002");

bool KvcacheConnFault002::IsValid(const std::vector<std::string> &fields)
{
    int statusCode = std::stoi(fields[7]);
    const std::string &respMsg = fields[12];
    return (statusCode == 2 || statusCode == 3 || statusCode == 8 || (statusCode == 0 && !respMsg.empty()));
}

std::string KvcacheConnFault002::GetName() const
{
    return "用户侧错误（code=0/respMsg异常 + code=2/3/8）";
}

std::string KvcacheConnFault002::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause KvcacheConnFault002::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault002::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string KvcacheConnFault002::GetValidationMethodDesc() const
{
    return "通过access log识别（来源：08手册:L127-130, L187-190）："
           "查询access log respMsg，code=0配合respMsg异常、"
           "或code=2(K_INVALID)/3(K_NOT_FOUND)/8(K_NOT_READY)。";
}

std::string KvcacheConnFault002::GetId() const
{
    return "kvcache_conn_fault_002";
}
}